package org.apache.commons.time;

public final class TimeComparator {
    private TimeComparator() {}
    public static int compare(long t1Millis, long t2Millis) { return Long.compare(t1Millis, t2Millis); }
    public static boolean betweenInclusive(long t, long start, long end) {
        if (end < start) throw new IllegalArgumentException("end < start");
        return t >= start && t <= end;
    }
}
