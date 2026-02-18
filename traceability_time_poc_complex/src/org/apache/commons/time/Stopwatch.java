
package org.apache.commons.time;
public class Stopwatch {
    private long start = -1;
    public void start() {
        start = System.currentTimeMillis();
    }
    public long elapsed() {
        if (start < 0) throw new IllegalStateException();
        return System.currentTimeMillis() - start;
    }
}
