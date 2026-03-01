
package org.apache.commons.time;
public class Period {
    private final int days;
    public Period(int days) {
        if (days < 0) throw new IllegalArgumentException();
        this.days = days;
    }
    public int getDays() { return days; }
}
