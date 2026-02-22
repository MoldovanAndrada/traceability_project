package org.apache.commons.time;

/**
 * Orchestrates scheduling decisions using ranges, intervals and deadlines.
 */
public final class SchedulingService {
    private SchedulingService() {}

    public static boolean isWithinWindow(long nowMillis, DateRange window){
        if (window == null) throw new IllegalArgumentException("null window");
        return window.contains(nowMillis);
    }

    public static boolean conflicts(Interval a, Interval b){
        if (a == null || b == null) return false;
        return a.overlaps(b);
    }

    public static boolean deadlineExpired(long deadlineMillis, Clock clock){
        if (clock == null) throw new IllegalArgumentException("null clock");
        return Scheduler.expired(deadlineMillis, clock.nowMillis());
    }

    public static long timeRemaining(long deadlineMillis, long nowMillis){
        return Scheduler.remainingMillis(deadlineMillis, nowMillis);
    }
}
