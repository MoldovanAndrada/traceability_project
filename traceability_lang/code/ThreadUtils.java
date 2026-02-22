package org.apache.commons.lang3;

public class ThreadUtils {
    public static String currentName() {
        return Thread.currentThread().getName();
    }
    public static void sleepQuietly(long millis) {
        try { Thread.sleep(millis); } catch (InterruptedException ignored) { Thread.currentThread().interrupt(); }
    }
}
