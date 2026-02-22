package org.apache.commons.lang3;

public class ArrayUtils {

    public static void reverseArray(char[] a) {
        if (a == null) return;
        int len = a.length;
        for (int i = 0; i < len / 2; i++) {
            char t = a[i];
            a[i] = a[len - 1 - i];
            a[len - 1 - i] = t;
        }
    }

    public static char[] copyOf(char[] a) {
        if (a == null) return null;
        char[] r = new char[a.length];
        System.arraycopy(a, 0, r, 0, a.length);
        return r;
    }

    public static boolean isEmpty(char[] a) {
        return a == null || a.length == 0;
    }

    public static int safeLength(char[] a) {
        return a == null ? 0 : a.length;
    }
}
