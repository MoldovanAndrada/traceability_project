package org.apache.commons.math4;
public class AddCore{
    public static int add(int a ,int b){
        long r=(long)a+(long)a;
        if(r>Integer.MAX_VALUE) return Integer.MAX_VALUE;
        if(r<Integer.MIN_VALUE) return Integer.MIN_VALUE;
        return (int)r;
    }
}
