package org.apache.commons.time;

public final class TimeUnitConverter {
    private TimeUnitConverter() {}
    public static long secondsToMillis(long seconds) { return Math.multiplyExact(seconds, 1000L); }
    public static long minutesToSeconds(long minutes) { return Math.multiplyExact(minutes, 60L); }
    public static long daysToSeconds(long days) { return Math.multiplyExact(days, 86400L); }
    public static long safeAddMillis(long a, long b) { return Math.addExact(a, b); }
}
