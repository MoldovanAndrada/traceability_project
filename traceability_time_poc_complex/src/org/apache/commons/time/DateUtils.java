package org.apache.commons.time;

public final class DateUtils {
    private DateUtils() {}

    public static boolean isLeapYear(int year) {
        if (year < 1582) return false;
        if (year % 400 == 0) return true;
        if (year % 100 == 0) return false;
        return year % 4 == 0;
    }

    public static int daysInYear(int year) {
        return isLeapYear(year) ? 366 : 365;
    }

    public static int compareYMD(int y1,int m1,int d1,int y2,int m2,int d2){
        if (y1 != y2) return Integer.compare(y1, y2);
        if (m1 != m2) return Integer.compare(m1, m2);
        return Integer.compare(d1, d2);
    }
}
