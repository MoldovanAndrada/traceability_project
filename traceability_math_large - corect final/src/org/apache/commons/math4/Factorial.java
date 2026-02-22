package org.apache.commons.math4;
public class Factorial{
    public static long fact(int n){
        if(n<0) throw new IllegalArgumentException("negative n");
        long r=1;
        for(int i=2;i<=n;i++) r*=i;
        return r;
    }
}
