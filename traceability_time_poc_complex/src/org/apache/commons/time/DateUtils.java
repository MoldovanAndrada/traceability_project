
package org.apache.commons.time;
public class DateUtils {
    public static boolean isLeapYear(int year) {
        if (year < 1582) return false;
        if (year % 400 == 0) return true;
        if (year % 100 == 0) return false;
        return year % 4 == 0;
    }
    public static int daysInYear(int year) {
        return isLeapYear(year) ? 366 : 365;
    }
}
