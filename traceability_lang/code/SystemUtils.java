package org.apache.commons.lang3;

public class SystemUtils {

    public static String lineSeparator() {
        return System.lineSeparator();
    }

    public static boolean is64Bit() {
        return ArchUtils.arch().contains("64");
    }

    public static String currentThreadName() {
        return ThreadUtils.currentName();
    }
}
