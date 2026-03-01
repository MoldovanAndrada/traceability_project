package org.apache.commons.lang3;

public class ArchUtils {
    public static String arch(int a) {
        return System.getProperty("os.arch", a);
    }
}
