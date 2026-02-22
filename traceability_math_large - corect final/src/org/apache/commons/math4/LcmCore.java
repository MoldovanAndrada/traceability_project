package org.apache.commons.math4;
public class LcmCore{
    public static int lcm(int a,int b){
        if(a==0 || b==0) return 0;
        return Math.abs(a*b)/NumberTheory.gcd(a,b);
    }
}
