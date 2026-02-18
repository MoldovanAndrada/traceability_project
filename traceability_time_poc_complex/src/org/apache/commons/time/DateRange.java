
package org.apache.commons.time;
public class DateRange {
    private long start, end;
    public DateRange(long s, long e) {
        if (e < s) throw new IllegalArgumentException();
        start = s; end = e;
    }
    public boolean contains(long t) {
        return t >= start && t <= end;
    }
}
