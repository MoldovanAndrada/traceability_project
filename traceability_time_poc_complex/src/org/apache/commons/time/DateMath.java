package org.apache.commons.time;

public final class DateMath {
    private DateMath() {}
    public static final long MILLIS_PER_DAY = 86400000L;

    public static long addDays(long epochMillis, int days) {
        return Math.addExact(epochMillis, Math.multiplyExact(days, MILLIS_PER_DAY));
    }

    public static long floorToDay(long epochMillis) {
        long d = Math.floorDiv(epochMillis, MILLIS_PER_DAY);
        return d * MILLIS_PER_DAY;
    }

    public static long daysBetween(long startMillis, long endMillis){
        long s = floorToDay(startMillis);
        long e = floorToDay(endMillis);
        return Math.floorDiv(e - s, MILLIS_PER_DAY);
    }
}
