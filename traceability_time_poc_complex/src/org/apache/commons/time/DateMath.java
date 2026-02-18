
package org.apache.commons.time;
public class DateMath {
    public static long addDays(long millis, int days) {
        return Math.addExact(millis, days * 86400000L);
    }
}
