#include "constitutive.h"
#include <cmath>

namespace fco {

double Concreto::fcd_kncm2() const {
    return (fck_mpa / gama_c) * 0.1;
}

double Concreto::eps_c2_pmilh() const {
    if (fck_mpa <= 50.0) return 2.0;
    return 2.0 + 0.085 * std::pow(fck_mpa - 50.0, 0.53);
}

double Concreto::eps_cu_pmilh() const {
    if (fck_mpa <= 50.0) return 3.5;
    const double t = (90.0 - fck_mpa) / 100.0;
    return 2.6 + 35.0 * std::pow(t, 4.0);
}

double Concreto::n_parabola() const {
    if (fck_mpa <= 50.0) return 2.0;
    const double t = (90.0 - fck_mpa) / 100.0;
    return 1.4 + 23.4 * std::pow(t, 4.0);
}

double strain_pmilh(
    double s, double x_LN, double h_inc, double d_inc_,
    double eps_c2, double eps_cu)
{
    const double x_lim_2_3 = eps_cu / (eps_cu + 10.0) * d_inc_;
    if (x_LN <= x_lim_2_3) {
        // Dominio 2: pivo A
        return 10.0 * (x_LN - s) / (d_inc_ - x_LN);
    }
    if (x_LN <= h_inc) {
        // Dominio 3/4/4a: pivo B
        return eps_cu * (x_LN - s) / x_LN;
    }
    // Dominio 5: pivo C em s = 3*h_inc/7
    return eps_c2 * (x_LN - s) / (x_LN - 3.0 * h_inc / 7.0);
}

double sigma_concreto(
    double eps, double fcd, double eps_c2, double eps_cu, double n_par)
{
    // Tracao ou nao-comprimido -> 0
    if (eps <= 0.0) return 0.0;
    if (eps >= eps_cu) return 0.0;  // ultrapassou ruptura
    if (eps >= eps_c2) {
        // Patamar plastico
        return ALPHA_C * fcd;
    }
    // Parabolica: sigma = alpha_c * fcd * (1 - (1 - eps/eps_c2)^n)
    const double r = 1.0 - eps / eps_c2;
    return ALPHA_C * fcd * (1.0 - std::pow(r, n_par));
}

double sigma_aco(double eps, double fyd, double Es, double eps_yd) {
    const double abs_eps = std::abs(eps);
    if (abs_eps <= eps_yd) {
        return eps / 1000.0 * Es;
    }
    return (eps > 0 ? 1.0 : -1.0) * fyd;
}

}  // namespace fco
