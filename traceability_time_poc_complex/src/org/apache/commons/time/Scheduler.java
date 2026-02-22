package org.apache.commons.time;

public final class Scheduler {
    private Scheduler() {}
    public static boolean expired(long deadlineMillis, long nowMillis) { return nowMillis > deadlineMillis; }
    public static long remainingMillis(long deadlineMillis, long nowMillis) {
        long r = deadlineMillis - nowMillis;
        return r < 0 ? 0 : r;
    }
}
