package org.apache.commons.time;

/**
 * Orchestrates validation and unit conversions for time-of-day & epoch operations.
 */
public final class TimeService {
    private TimeService() {}

    public static long addSecondsToEpoch(long epochMillis, long seconds){
        long delta = TimeUnitConverter.secondsToMillis(seconds);
        return TimeUnitConverter.safeAddMillis(epochMillis, delta);
    }

    public static long normalizeEpochToDaySeconds(long epochMillis){
        long seconds = EpochConverter.millisToSeconds(epochMillis);
        return EpochConverter.normalizeSecondsWithinDay(seconds);
    }

    public static void validateTimeOfDay(int h, int m, int s){
        TimeValidator.validateHMS(h, m, s);
    }

    public static int compareEpoch(long aMillis, long bMillis){
        return TimeComparator.compare(aMillis, bMillis);
    }

    public static int offsetMinutes(String tz){
        return TimeZoneRules.offsetMinutes(tz);
    }
}
