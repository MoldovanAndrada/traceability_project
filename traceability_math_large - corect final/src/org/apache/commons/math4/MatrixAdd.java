package org.apache.commons.math4;
public class MatrixAdd{
    public static int[][] add(int[][]a,int[][]b){
        if(a==null || b==null) throw new IllegalArgumentException("null matrix");
        if(a.length==0 || b.length==0) throw new IllegalArgumentException("empty matrix");
        if(a.length!=b.length || a[0].length!=b[0].length) throw new IllegalArgumentException("dimension mismatch");
        int[][]r=new int[a.length][a[0].length];
        for(int i=0;i<a.length;i++)
            for(int j=0;j<a[0].length;j++)
                r[i][j]=a[i][j]+b[i][j];
        return r;
    }
}
