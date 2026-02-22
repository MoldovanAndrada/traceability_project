package org.apache.commons.time;

public final class EpochConverter {
    private EpochConverter() {}
    public static long millisToSeconds(long ms) { return ms / 1000L; }
    public static long secondsToMillis(long seconds) { return Math.multiplyExact(seconds, 1000L); }
    public static long normalizeSecondsWithinDay(long seconds) {
        long s = seconds % 86400L;
        return s < 0 ? s + 86400L : s;
    }
}
