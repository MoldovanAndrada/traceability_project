package org.apache.commons.time;

public final class CalendarUtils {
    private CalendarUtils() {}

    public static boolean isValidMonth(int month) {
        return month >= 1 && month <= 12;
    }

    public static int daysInMonth(int month, int year) {
        if (!isValidMonth(month)) throw new IllegalArgumentException("Invalid month: " + month);
        switch (month) {
            case 2: return DateUtils.isLeapYear(year) ? 29 : 28;
            case 4: case 6: case 9: case 11: return 30;
            default: return 31;
        }
    }

    public static boolean isValidDay(int year, int month, int day) {
        if (!isValidMonth(month)) return false;
        if (day < 1) return false;
        return day <= daysInMonth(year, month);
    }

    public static int dayOfYear(int year, int month, int day) {
        if (!isValidDay(year, month, day)) throw new IllegalArgumentException("Invalid date");
        int doy = 0;
        for (int m = 1; m < month; m++) doy += daysInMonth(year, m);
        return doy + day;
    }
}
