package org.apache.commons.time;

public class Clock {
    public long nowMillis() { return System.currentTimeMillis(); }
    public long monotonicNanos() { return System.nanoTime(); }
}
