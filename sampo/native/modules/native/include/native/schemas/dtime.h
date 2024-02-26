#ifndef NATIVE_TIME_H
#define NATIVE_TIME_H

class Time {
private:
    int value;

public:
    Time(int value = 0);

    static Time inf();

    static Time unassigned();

    bool is_unassigned() const;

    bool is_inf() const;

    Time operator+(Time &other) const;

    Time operator+(int other) const;

    Time operator-(Time &other) const;

    Time operator-(int other) const;

    Time operator*(Time &other) const;

    Time operator*(int other) const;

    Time operator/(Time &other) const;

    Time operator/(int other) const;

    bool operator<(Time &other) const;

    bool operator<(int other) const;

    bool operator>(Time &other) const;

    bool operator>(int other) const;

    bool operator<=(Time &other) const;

    bool operator<=(int other) const;

    bool operator>=(Time &other) const;

    bool operator>=(int other) const;

    bool operator==(Time &other) const;

    bool operator==(int other) const;
};

#endif    // NATIVE_TIME_H
