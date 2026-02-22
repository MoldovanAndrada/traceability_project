package org.apache.commons.time;

public final class DateFormatter {
    private DateFormatter() {}

    public static String formatISO(int y, int m, int d) {
        if (y < 0 || y > 9999) throw new IllegalArgumentException("bad year");
        if (m < 1 || m > 12) throw new IllegalArgumentException("bad month");
        if (d < 1 || d > 31) throw new IllegalArgumentException("bad day");
        return String.format("%04d-%02d-%02d", y, m, d);
    }

    public static String formatCompact(int y, int m, int d) {
        return String.format("%04d%02d%02d", y, m, d);
    }
}
