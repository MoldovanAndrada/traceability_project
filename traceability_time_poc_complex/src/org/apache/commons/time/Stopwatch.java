package org.apache.commons.time;

public final class Stopwatch {
    private long startNanos = -1L;
    private long endNanos = -1L;

    public void start(){ startNanos = System.nanoTime(); endNanos = -1L; }
    public void stop(){ if(startNanos < 0) throw new IllegalStateException("Not started"); endNanos = System.nanoTime(); }

    public long elapsedMillis(){
        if(startNanos < 0) throw new IllegalStateException("Not started");
        long end = (endNanos >= 0) ? endNanos : System.nanoTime();
        return (end - startNanos) / 1_000_000L;
    }
}
