
package org.apache.commons.time;
public class TimeValidator {
    public static void validateHour(int h) {
        if (h < 0 || h > 23) throw new IllegalArgumentException();
    }
}
