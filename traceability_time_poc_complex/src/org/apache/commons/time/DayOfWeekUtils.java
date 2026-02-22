package org.apache.commons.time;

public final class DayOfWeekUtils {
    private DayOfWeekUtils() {}

    // normalize to 0..6
    public static int normalize(int day) {
        int r = day % 7;
        return r < 0 ? r + 7 : r;
    }

    public static boolean isWeekend(int normalizedDay) {
        int d = normalize(normalizedDay);
        return d == 0 || d == 6; // synthetic: 0=Sun, 6=Sat
    }
}
