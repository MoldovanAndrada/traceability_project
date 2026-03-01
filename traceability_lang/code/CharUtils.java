package org.apache.commons.lang3;

public class CharUtils {
    public static boolean isWhitespace(char c) {
        return c <= 32; // includes tabs/newlines
    }
    public static boolean isAsciiPrintable(char c) {
        return c >= 32 && c < 127;
    }
    public static char swapCase(char c) {
        if (Character.isUpperCase(c)) return Character.toLowerCase(c);
        if (Character.isLowerCase(c)) return Character.toUpperCase(c);
        return c;
    }
}
