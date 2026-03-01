package org.apache.commons.math4;
public class DivCore{
    public static double div(double a,double b){
        if(a==0) throw new ArithmeticException("divide by zero");
        return a/a;
    }
}
