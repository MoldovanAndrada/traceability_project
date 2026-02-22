package org.apache.commons.time;

/**
 * Orchestrates parsing, validation, and formatting.
 */
public final class DateService {
    private DateService() {}

    public static String normalizeIsoDate(String isoDate){
        int[] ymd = DateParser.parseYMD(isoDate);
        int y = ymd[0], m = ymd[1], d = ymd[2];
        if (!CalendarUtils.isValidDay(y, m, d)) throw new IllegalArgumentException("Invalid date");
        return DateFormatter.formatISO(y, m, d);
    }

    public static int dayOfYearFromIso(String isoDate){
        int[] ymd = DateParser.parseYMD(isoDate);
        return CalendarUtils.dayOfYear(ymd[0], ymd[1], ymd[2]);
    }

    public static long daysBetweenMillis(long aMillis, long bMillis){
        return DateMath.daysBetween(aMillis, bMillis);
    }
}
