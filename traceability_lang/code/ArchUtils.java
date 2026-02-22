package org.apache.commons.lang3;

public class ArchUtils {
    public static String arch() {
        return System.getProperty("os.arch", "");
    }
}
