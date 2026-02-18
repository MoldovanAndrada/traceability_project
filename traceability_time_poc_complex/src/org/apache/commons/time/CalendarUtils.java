
package org.apache.commons.time;
public class CalendarUtils {
    public static int daysInMonth(int year, int month) {
        switch (month) {
            case 2: return DateUtils.isLeapYear(year) ? 29 : 28;
            case 4: case 6: case 9: case 11: return 30;
            default: return 31;
        }
    }
}
