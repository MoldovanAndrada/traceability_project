package org.apache.commons.math4;
public class LcmCore{
    public static int lcm(int a,int b){
        return Math.abs(a*b)/NumberTheory.gcd(a,b);
    }
}
