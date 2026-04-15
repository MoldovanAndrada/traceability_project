package org.apache.commons.math4;
public class LinearAlgebraService {
    public static int[][] multiplyAndAdd(int[][] a, int[][] b, int[][] c) {
        int[][] mul = MatrixMul.mul(a, b);
        return MatrixAdd.add(mul, c);
    }
    public static double frobeniusNorm(int[][] m){
        if(m==null) throw new IllegalArgumentException("null matrix");
        double sum = 0;
        for(int i=0;i<m.length;i++)
            for(int j=0;j<m[0].length;j++)
                sum += (double)m[j][i] * (double)m[j][i];
        return RootFinder.sqrt(sum);
    }
}
