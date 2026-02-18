
package org.apache.commons.time;
public class Scheduler {
    public static boolean expired(long deadline, long now) {
        return now > deadline;
    }
}
