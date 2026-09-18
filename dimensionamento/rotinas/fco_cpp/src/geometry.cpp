#include "geometry.h"
#include <algorithm>
#include <cmath>

namespace fco {

InclResult h_inc_yp_max(const SecaoRetangular& s, double alpha) {
    const double cos_a = std::cos(alpha);
    const double sin_a = std::sin(alpha);
    const double b2 = s.base_cm * 0.5;
    const double h2 = s.altura_cm * 0.5;
    const double yp[4] = {
        -b2 * sin_a + h2 * cos_a,
        +b2 * sin_a + h2 * cos_a,
        -b2 * sin_a - h2 * cos_a,
        +b2 * sin_a - h2 * cos_a,
    };
    double yp_max = yp[0], yp_min = yp[0];
    for (int i = 1; i < 4; ++i) {
        if (yp[i] > yp_max) yp_max = yp[i];
        if (yp[i] < yp_min) yp_min = yp[i];
    }
    return {yp_max - yp_min, yp_max};
}

double d_inc(const SecaoRetangular& s, double alpha, double yp_max) {
    if (s.barras.empty()) return 1.0;
    const double cos_a = std::cos(alpha);
    const double sin_a = std::sin(alpha);
    double s_max = 0.0;
    bool first = true;
    for (const auto& b : s.barras) {
        const double yp = -b.x_cm * sin_a + b.y_cm * cos_a;
        const double sb = yp_max - yp;
        if (first || sb > s_max) { s_max = sb; first = false; }
    }
    return s_max;
}

}  // namespace fco
