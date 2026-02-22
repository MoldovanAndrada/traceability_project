package org.apache.commons.math4;
public class NumberTheoryService {
    public static boolean areCoprime(int a, int b) {
        return NumberTheory.gcd(a, b) == 1;
    }
    public static int fibGcd(int n, int m) {
        int f1 = Fibonacci.fib(n);
        int f2 = Fibonacci.fib(m);
        return NumberTheory.gcd(f1, f2);
    }
    public static int safeLcm(int a, int b) {
        return LcmCore.lcm(a, b);
    }
}
