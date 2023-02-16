import numpy as np
from scipy.interpolate import interp1d
import pandas as pd
import os

DIR_PARAMS = './data/params'
FILE_PGD_LOWER = 'PGDcurve_lowerBound.csv'
FILE_PGD_UPPER = 'PGDcurve_upperBound.csv'

criticalAccelerationOfEachSoilType = [0.60, 0.50, 0.40, 0.35, 0.30, 0.25, 0.20, 0.15, 0.10, 0.05]
nSoilTypes = len(criticalAccelerationOfEachSoilType)

displacementFactorUpperBounds = pd.read_csv(os.path.join(DIR_PARAMS, FILE_PGD_UPPER), names=['ac/ais', 'factor'])
displacementFactorLowerBounds = pd.read_csv(os.path.join(DIR_PARAMS, FILE_PGD_LOWER), names=['ac/ais', 'factor'])

logDisplacementFactorUpperBound = interp1d(
    displacementFactorUpperBounds['ac/ais'],np.log(displacementFactorUpperBounds['factor']),
    fill_value='extrapolate')

logDisplacementFactorLowerBound = interp1d(
    displacementFactorLowerBounds['ac/ais'], np.log(displacementFactorLowerBounds['factor']),
    fill_value='extrapolate')


class District(object):

    def __init__(self, **kwargs):

        self.GIS_ID = kwargs['GIS_ID'] # can be a vector
        self.area = kwargs['area'] # m2
        self.nDamagedBuildings = kwargs['nDamagedBuildings'] # can be a vector

        assert len(kwargs['soilProportion']) == 10, 'Soil proportion must be 10 categories'
        self.soilProportion = kwargs['soilProportion'] # Proportions of 10 landslide-susceptibility categories (ref. HAZUS-EQ model)

        assert isinstance(kwargs['GM_ID'], (int, np.integer)), 'A district must correspond to exactly one ground motion area.'
        self.GM_ID = kwargs['GM_ID'] # Corresponding Ground Motion area

        self.pgd = None
        self.nodes_ID = kwargs['nodes_ID']

    def __repr__(self):
        return repr(f'Area(m2): {self.area:.3f}, nDamaged: {self.nDamagedBuildings}, Nodes: {self.nodes_ID}, GM_ID: {self.GM_ID}')

def number_of_cycles(Mw):
    '''
    HAZUS Eq. 4-15 based on Seed and Idriss (1982)
    A relationship between number of cycles and earthquake moment magnitude
    '''
    return 0.3419 * np.power(Mw, 3) - 5.5214 * np.power(Mw, 2) + 33.6154 * Mw - 70.7692


def samplePgdInInch(row, gms, nSample):
    '''
    HAZUS 4.2.2

    E(PGD] = E[d/ais] * ais * n

    E[PGD]: expected permanent ground displacments due to landslide
    E[d/ais]: expected displacement factor
    ais: induced acceleration (in decimal fraction of g's)
    n: number of cycles

    row: pd.DataFrame row of district_table
    gms: Dict dic of instances of GM
    nSample: int

    #FIXIT
    can be vectorised
    '''
    # Constant parameters
    # Sampling
    #nDistrict = length( districts )
    #for iDistInd in range(nDistrict):

    mw = gms[row['GM_ID']].Mw
    pga = gms[row['GM_ID']].PGA

    #iPgd_inchSampleArray = np.zeros( 1, nSample )
    pgd = np.zeros(nSample)
    for i in range(nSample):
        #ijSoilType = randsample( nSoilTypes, 1, true, iSoilProportions )
        criticalAcceleration = np.random.choice(criticalAccelerationOfEachSoilType, size=1, p=row['soilProportion'])

        accelerationRatio = criticalAcceleration / pga

        if accelerationRatio > 1:
            displacementFator = 0.0

        else:
            displacementFactorUpperBound = np.exp(logDisplacementFactorUpperBound(accelerationRatio))
            displacementFactorLowerBound = max(np.exp(logDisplacementFactorLowerBound(accelerationRatio)), 0)

            if displacementFactorUpperBound > 0:
                randForDisplacementFactor = np.random.rand(1)
                logDisplacementFator = np.log(displacementFactorLowerBound) + randForDisplacementFactor * (
                    np.log(displacementFactorUpperBound) - np.log(displacementFactorLowerBound))
                displacementFator = np.exp(logDisplacementFator)
            else:
                displacementFator = 0

        pgd[i] = displacementFator * pga * number_of_cycles(mw)


    return pgd

def convertGisId2arrayId(objects):
    # copied from convertGisId2arrayId.m

    #gisIds = arrayfun( @(x) x.GIS_ID, objects )
    gisId_min = min(gisIds)
    gisId_max = max(gisIds)
    gisId2arrayId = zeros( (gisId_max-gisId_min)+1, 1 ) # GIS IDs can start from 0.

    nObject = length(objects)
    for iArrayId in range(nObject):
        iGisId = objects(iArrayId).GIS_ID
        gisId2arrayId[ iGisId-gisId_min+1 ] = iArrayId
    end

    return gisId2arrayId, gisId_min


'''
# copied from addGMId.m
    def addGMId(self, GMs, districtGmJoin_array):

        # Get pointer from GM GIS ID to array ID (for computation efficiency)
        #gmGisIds = arrayfun( @(x) x.GIS_ID, GMs )
        gmGisId_min = min(gmGisIds)
        gmGisId_max = max(gmGisIds)
        gmId_gis2array = zeros( (gmGisId_max-gmGisId_min)+1, 1 ) # GIS IDs can start from 0.

        nGM = length(GMs)
        for iGMArrayId in range(nGM):
            iGMGisId = GMs(iGMArrayId).GIS_ID
            #gmId_gis2array( iGMGisId-gmGisId_min+1 ) = iGMArrayId
        end

        # Match each district to a GM region
        nDistrict = length( districts )
        for iDistrictIndex in range(nDistrict):

            iDistrict = districts( iDistrictIndex )
            iDistrict_gisId = iDistrict.GIS_ID

            #iGM_gisId = districtGmJoin_array( districtGmJoin_array( :, 1 ) == iDistrict_gisId, 2 )
            iGmArrayIds = gmId_gis2array( iGM_gisId-gmGisId_min+1 )
            if length( iGmArrayIds ) > 2:
                error( 'A district must be associated with exactly one GM region.' )
            else:
                districts(iDistrictIndex).GM_ID = iGmArrayIds

#copied from addNodes.m
    def addNodes(self, nodes, nodeDistrictJoin_array):

        [nodeGisId2arrayId, nodeGisId_min] = convertGisId2arrayId( nodes )

        for iDistInd, _ in enumerate(districts):
            iDistGisId = districts(iDistInd).GIS_ID
            iNodeGisId = nodeDistrictJoin_array( nodeDistrictJoin_array[:,2] == iDistGisId, 1 )

            iNodeArrayId = nodeGisId2arrayId( iNodeGisId - nodeGisId_min + 1 )
            districts(iDistInd).nodes_ID = iNodeArrayId[:]
'''


