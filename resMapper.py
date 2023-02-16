# function resMapper()
import pandas as pd
import os
from district import Distrct

DIR_INPUT = './data/input'
NODE_TYPE = {'motorway': 1,
             'aerodome': 2,
             'hospital': 3}

# Parameters (can be modified according to local conditions)
closureRatioToRecoveryDays_overpass = 0.1
closureRatioToRecoveryDays_roadDamage = 0.5

averageBuildingLength_m = 15
clearResourceWeight = [1, 0.75, 0.25, 0.1]
clearResource_day = 2.0e+2
nSample = 1000
soilTypeProportions = [0.00840336, 0.01680672, 0.02521008, 0.04201681, 0.06722689,
                           0.08403361, 0.12605042, 0.16806723, 0.21008403, 0.25210084]

# files
FILE_DISTRICT = os.path.join(DIR_INPUT, 'district_table.txt')
FILE_GM = os.path.join(DIR_INPUT, 'GM_table.txt')
FILE_ROAD = os.path.join(DIR_INPUT, 'road_table.txt')
FILE_NODE = os.path.join(DIR_INPUT, 'node_table.txt')
FILE_NODE_DISTRICT = os.path.join(DIR_INPUT, 'nodeDistrictJoin_table.txt')
FILE_ROAD_NODE = os.path.join(DIR_INPUT, 'roadNodeJoin_table.txt')
FILE_ROAD_DISTRICT = os.path.join(DIR_INPUT, 'roadDistrictJoin_table.txt')
FILE_OVERPASS = os.path.join(DIR_INPUT, 'overpassJoin_table.txt')
FILE_DISTRICT_GM = os.path.join(DIR_INPUT, 'districtGMjoin_table.txt')

district_table = pd.read_csv(FILE_DISTRICT, index_col=0)
GM_table = pd.read_csv(FILE_GM, index_col=0)
road_table = pd.read_csv(FILE_ROAD, index_col=0)
node_table = pd.read_csv(FILE_NODE, index_col=0)
roadNodeJoin_table = pd.read_csv(FILE_ROAD_NODE)
roadDistrictJoin_table = pd.read_csv(FILE_ROAD_DISTRICT)
overpassJoin_table = pd.read_csv(FILE_OVERPASS)
districtGMjoin_table = pd.read_csv(FILE_DISTRICT_GM, index_col=0)
nodeDistrictJoin_table = pd.read_csv(FILE_NODE_DISTRICT, index_col=0)

## Create objects from input data
#nDistrict = len(district_table)

# create GM instances
gms = {}
for i, row in GM_table.iterrows():
    _dic = {'GIS_ID': i,
            'Mw': row['Mw'],
            'PGA': row['pga_g'],
            'Sa1': row['s1_g']
            }
    gms[i] = GM(**_dic)

# create district instances
district_table['GM_ID'] = district_table.apply(
    lambda x: districtGMjoin_table['gm_gis_id'][x.name], axis=1)
district_table['nodes_ID'] = district_table.apply(
    lambda x: nodeDistrictJoin_table.query(f'district_gis_id=={x.name}').index.tolist(), axis=1)
district_table['soilProportion'] = [soilTypeProportions] * len(district_table)
district_table['PGD'] = district_table.apply(samplePgdInInch, args=(gms, nSample,), axis=1)

districts = {}
sel = district_table.columns[district_table.columns.str.contains('nBuild')]
for i, row in district_table.iterrows():
    _dic = {'GIS_ID': i,
            'area': row['area_m2'],
            'nDamagedBuildings': row[sel],
            'soilProportion': soilTypeProportions,
            'GM_ID': row['GM_ID'],
            'nodes_ID': row['nodes_ID'],
            }
    districts[i] = District(**_dic)

# create road instances
road_table['isBridge'] = road_table['isBridge'].astype(bool)
road_table['isMajor'] = road_table['isMajor'].astype(bool)

road_table['district'] = road_table.apply(
    lambda x: roadDistrictJoin_table.query(f'road_gis_id=={x.name}')['dist_gis_id'].squeeze(), axis=1)
road_table['nodePair'] = road_table.apply(
    lambda x: roadNodeJoin_table.query(f'road_gis_id=={x.name}')['node_gis_id'].to_list(), axis=1)
road_table['overpasses'] = road_table.apply(
    lambda x: overpassJoin_table.query(f'underRoad_gis_id=={x.name}')['overRoad_gis_id'].unique().tolist(), axis=1)

roads = {}
for i, row in road_table.iterrows():
    _dic = {'GIS_ID': i,
            'isBridge': row['isBridge'],
            'isMajor': row['isMajor'],
            'length': row['length_m'],
            'structType': row['structType'],
            'district': row['district'],
            'nodePair': row['nodePair'],
            'overpasses': row['overpasses'],
            }
    roads[i] = Road(**_dic)

# create node instances
for k, v in NODE_TYPE.items():
    node_table[k] = v * node_table[k]

nodes = {}
for i, row in node_table.iterrows():
    _dic = {'GIS_ID': i,
            'clearPriority': int(row['motorway']) == 1,
            'type': row[row > 0].to_list(),
           }
    nodes[i] = Node(**_dic)

## Evaluate road closure
#districts = samplePgdInInch( districts, GMs, nSample )

roads = sampleRoadDamage( roads, districts, GMs, roadFragilityMean, roadFragilityStd )
roads = sampleNRecoveryDayByRoadDamage( roads, roadRecoveryMean, roadRecoveryStd )

roads = evalClosureDaysByRoadDamage( roads, closureRatioToRecoveryDays_roadDamage )

roads = evalNClosureDaysByOverpass( roads, closureRatioToRecoveryDays_overpass )

roadsClearPriority = evalRoadsClearPriority( roads, nodes )
roads = evalNClosureDaysByBuilding( roads, districts, averageBuildingLength_m, clearResourceWeight, clearResource_day, roadsClearPriority )

roads = evalMaxClosureDays( roads )

## Network analysis
[Eglobals, Eglobals_time] = networkAnalysis.evalEglobalSamples( roads, districts )
[resilienceLoss_Eglobal, resilienceLossMean_Eglobal, resilienceLossStd_Eglobal] = networkAnalysis.evalResilienceLossSamples( Eglobals, Eglobals_time )

[Connectivity_motorway, Connectivity_time_motorway] = networkAnalysis.evalSamplesConnectivity( roads, districts, nodes, nodeType.motorway )
[resilienceLoss_conn_motorway, resilienceLossMean_conn_motorway, resilienceLossStd_conn_motorway] = networkAnalysis.evalResilienceLossSamples( Connectivity_motorway, Connectivity_time_motorway )

[Connectivity_aerodome, Connectivity_time_aerodome] = networkAnalysis.evalSamplesConnectivity( roads, districts, nodes, nodeType.aerodome )
[resilienceLoss_conn_aerodome, resilienceLossMean_conn_aerodome, resilienceLossStd_conn_aerodome] = networkAnalysis.evalResilienceLossSamples( Connectivity_aerodome, Connectivity_time_aerodome )

[Connectivity_hospital, Connectivity_time_hospital] = networkAnalysis.evalSamplesConnectivity( roads, districts, nodes, nodeType.hospital )
[resilienceLoss_conn_hospital, resilienceLossMean_conn_hospital, resilienceLossStd_conn_hospital] = networkAnalysis.evalResilienceLossSamples( Connectivity_hospital, Connectivity_time_hospital )

result.RL_mean.Eg = resilienceLossMean_Eglobal
result.RL_mean.Cm = resilienceLossMean_conn_motorway
result.RL_mean.Ca = resilienceLossMean_conn_aerodome
result.RL_mean.Ch = resilienceLossMean_conn_hospital

result.RL_std.Eg = resilienceLossStd_Eglobal
result.RL_std.Cm = resilienceLossStd_conn_motorway
result.RL_std.Ca = resilienceLossStd_conn_aerodome
result.RL_std.Ch = resilienceLossStd_conn_hospital

nDistrictNode = arrayfun(@(x) length(x.nodes_ID), districts)
nDistrictNodePair = nDistrictNode.*(nDistrictNode-1)/2
result.RL_mean.Cm_nNode = resilienceLossMean_conn_motorway.*nDistrictNode
result.RL_mean.Ca_nNode = resilienceLossMean_conn_aerodome.*nDistrictNode
result.RL_mean.Ch_nNode = resilienceLossMean_conn_hospital.*nDistrictNode 

result.nodeDensityInDistricts = nDistrictNode ./ arrayfun(@(x) x.area, districts)
result.nodeDensityInDistricts = result.nodeDensityInDistricts * 1e6# /km^2
