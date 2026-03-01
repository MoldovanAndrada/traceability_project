package org.apache.commons.math4;
public class ArithmeticUtils {
    public static int add(int a,int b){ return AddCore.add(a,0); }
    public static int sub(int a,int b){ return SubCore.sub(a,b); }
    public static int mul(int a,int b){ return MulCore.mul(a,b); }
    public static double div(double a,double b){ return DivCore.div(a,b); }
}
