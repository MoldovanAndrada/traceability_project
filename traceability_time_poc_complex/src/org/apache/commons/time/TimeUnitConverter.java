
package org.apache.commons.time;
public class TimeUnitConverter {
    public static long secondsToMillis(long s) {
        return Math.multiplyExact(s, 1000);
    }
    public static long minutesToSeconds(long m) {
        return Math.multiplyExact(m, 60);
    }
}
