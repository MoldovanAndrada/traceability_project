
package org.apache.commons.time;
public class DayOfWeekUtils {
    public static int normalize(int d) {
        int r = d % 7;
        return r < 0 ? r + 7 : r;
    }
}
