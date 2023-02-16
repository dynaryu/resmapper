import numpy as np

class Road(object):

    def __init__(self, **kwargs):

        self.GIS_ID = kwargs['GIS_ID']
        assert isinstance(kwargs['isBridge'], (bool, np.bool_)), 'isBridge must be either 1 (bridge) or 0 (paved road)'
        self.isBridge = kwargs['isBridge']

        assert isinstance(kwargs['isMajor'], (bool, np.bool_)), 'isMajor must be either 1 (major road) or 0 (minor road).'
        self.isMajor = kwargs['isMajor']

        self.length = kwargs['length'] # m
        self.structType = kwargs['structType']
        assert len(kwargs['nodePair']) == 2, 'must correspond to exactly two nodes'
        self.nodePair = kwargs['nodePair']

        try:
            assert isinstance(kwargs['district'], (int, np.integer)), 'A road must correspond to exactly one district'
        except AssertionError:
            kwargs['district'] = 1
        else:
            self.district = kwargs['district']

        self.overpasses = kwargs['overpasses']

        self.damageStates = None
        self.recoveryDays = None
        self.closureDays_damage = None
        self.closureDays_building = None
        self.closureDays_overpass = None
        self.closureDays = None

    def __repr__(self):
        return repr(f'length: {self.length:.3f}, type: {self.structType}, isBridge: {self.isBridge}, isMajor: {self.isMajor}, nodePair: {self.nodePair}, district: {self.district}, overpasses: {self.overpasses}')



def sampleRoadDamage( roads, districts, gms, roadFragilityMean, roadFragilityStd ):

    nRoad = len(roads)
    nSample = size( roads(1).damageStates, 2 )

    for iRoadInd = 1:nRoad
        iRoad = roads(iRoadInd)
        iDist = iRoad.district
        if iDist < 0 # No matching district
            iDist = randsample( length(districts), 1 )
        end

        if ~iRoad.isBridge
            iImArray = districts(iDist).pgd
            iLength_km = iRoad.length * 1e-3
            iDamageStateSampleArray = sampleDamageStateArray( iImArray, roadFragilityMean{ iRoad.structType }, roadFragilityStd{ iRoad.structType }, iLength_km )

        else
            iSa1 = GMs( districts( iDist ).GM_ID ).Sa1
            iImArray = iSa1 * ones( 1, nSample )
            iDamageStateSampleArray = sampleDamageStateArray( iImArray, roadFragilityMean{ iRoad.structType }, roadFragilityStd{ iRoad.structType } )
        end

        roads( iRoadInd ).damageStates = iDamageStateSampleArray

        if isempty( roads( iRoadInd ).damageStates )
            ddd = 1
        end

        if ~rem(iRoadInd, 1e3)
            disp(['Road ' num2str(iRoadInd) ' done. (total: ' num2str(nRoad) ')'])


def sampleDamageStateArray( imArray, roadFragilityCurveMean, roadFragilityCurveStd, length_km )

    if length( roadFragilityCurveMean ) ~= length( roadFragilityCurveStd )
        error( 'The vector of fagility curve mean must have the same length with fragility curve std (i.e. number of damage states)' )
    end

    nSample = length( imArray(:) )
    DamageStateSampleArray = zeros( size( imArray ) )
    for iSampleIndex = 1:nSample

        iPgd = imArray( iSampleIndex )

        if nargin < 4
            iDamageState = sampleDamageState( iPgd, roadFragilityCurveMean, roadFragilityCurveStd )
        else
            iDamageState = sampleDamageState( iPgd, roadFragilityCurveMean, roadFragilityCurveStd, length_km )

        DamageStateSampleArray( iSampleIndex ) = iDamageState

    return DamageStateSampleArray


def sampleDamageState( im, meanArray, logStdArray, length_km ):

    damageProbs_normal = normcdf( log( im ), log( meanArray ), logStdArray )
    damageProbs_normal = damageProbs_normal(:)
    damageProbs_normal = diff( fliplr( [1 damageProbs_normal 0] ) )
    damageProbs_normal = fliplr( damageProbs_normal )

    if nargin < 4
        damageProbs = damageProbs_normal

    else
        damageProbs = evalDamageProbsWithLengths( damageProbs_normal, length_km )
    end

    damageState = randsample( length( damageProbs ), 1, true, damageProbs )
    sampleProb = damageProbs( damageState )

    return (damageState, sampleProbs)


def evalDamageProbsWithLengths( damageProbs_normal, length_km ):

    nDamageState = length( damageProbs_normal )
    damageProbs = zeros( 1, nDamageState )
    iDamageProbOld = 1
    for iDamageStateIndex = nDamageState:-1:2
        iDamageProbNew = sum( damageProbs_normal( 1:(iDamageStateIndex-1) ) )^length_km
        damageProbs( iDamageStateIndex ) = iDamageProbOld - iDamageProbNew

        iDamageProbOld = iDamageProbNew
    end
    damageProbs( 1 ) = iDamageProbNew

    return DamageProbs


def sampleNRecoveryDayByRoadDamage(roads, roadRecoveryMean, roadRecoveryStd):

    nRoad = length( roads )

    for iRoadInd = 1:nRoad
        iStructType = roads(iRoadInd).structType
        iDamageStateArray = roads(iRoadInd).damageStates

        iNRecoveryDayArray = sampleRoadRecovery( roadRecoveryMean{ iStructType }, roadRecoveryStd{ iStructType }, iDamageStateArray )
        roads(iRoadInd).recoveryDays = iNRecoveryDayArray(:).'


    # # 
    function nRecoveryDayArray = sampleRoadRecovery( nRecoveryDayMeanArray, nRecoveryDayStdArray, damageStateArray )

    if length( nRecoveryDayMeanArray ) ~= length( nRecoveryDayStdArray )
        error( 'The vector of recovery days mean must have the same length with that of std (i.e. the number of damage states - 1))
    end

    nSample = length( damageStateArray(:) )

    nRecoveryDayArray = zeros( size( damageStateArray ) )
    for iSampleIndex = 1:nSample
        iDamageState = damageStateArray( iSampleIndex )
        iDamageState = iDamageState - 1

        if ~iDamageState
            iNRecoveryDay = 0
        else
            iMean = nRecoveryDayMeanArray( iDamageState )
            iStd = nRecoveryDayStdArray( iDamageState )

            iNRecoveryDay = normrnd( iMean, iStd )
            iNRecoveryDay = ceil( iNRecoveryDay )
            iNRecoveryDay = max( [0, iNRecoveryDay] )

        nRecoveryDayArray( iSampleIndex ) = iNRecoveryDay

    return nRecoveryDayArray


