package org.apache.commons.time;

/**
 * Single facade entry point to create non-local impact surfaces.
 */
public final class TimeFacade {
    private TimeFacade() {}

    public static String normalizeDate(String isoDate){
        return DateService.normalizeIsoDate(isoDate);
    }

    public static long addSeconds(long epochMillis, long seconds){
        return TimeService.addSecondsToEpoch(epochMillis, seconds);
    }

    public static boolean inWindow(long nowMillis, long startMillis, long endMillis){
        DateRange r = new DateRange(startMillis, endMillis);
        return SchedulingService.isWithinWindow(nowMillis, r);
    }

    public static boolean intervalsConflict(long aStart, long aEnd, long bStart, long bEnd){
        Interval ia = new Interval(aStart, aEnd);
        Interval ib = new Interval(bStart, bEnd);
        return SchedulingService.conflicts(ia, ib);
    }
}
