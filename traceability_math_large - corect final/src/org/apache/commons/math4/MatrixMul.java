package org.apache.commons.math4;
public class MatrixMul{
    public static int[][] mul(int[][]a,int[][]b){
        int n=a.length;
        int[][]r=new int[n][n];
        for(int i=0;i<n;i++)
            for(int j=0;j<n;j++)
                for(int k=0;k<n;k++)
                    r[i][j]+=a[i][k]*b[k][j];
        return r;
    }
}
