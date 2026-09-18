#include "constitutive.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <stdexcept>
#include <string>

namespace fco {

void validar_fck(double fck_mpa) {
    if (!(fck_mpa >= FCK_MIN && fck_mpa <= FCK_MAX)) {
        char buf[160];
        std::snprintf(buf, sizeof(buf),
                      "fck = %g MPa fora da faixa da NBR 6118:2026 (20 a 90 MPa).", fck_mpa);
        throw std::invalid_argument(buf);
    }
}

// Mesmas expressoes do nucleo normativo (dimensionamento/nucleo_nbr6118.py).
double Concreto::fcd_kncm2() const {
    return (fck_mpa / gama_c) / 10.0;
}

double Concreto::eta_c() const {
    if (fck_mpa <= 40.0) return 1.0;
    return std::pow(40.0 / fck_mpa, 1.0 / 3.0);
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

double Concreto::pico_kncm2() const {
    return ALPHA_C * eta_c() * fcd_kncm2();
}

double Concreto::pivo_c_rel() const {
    const double ecu = eps_cu_pmilh();
    return std::max(0.0, (ecu - eps_c2_pmilh()) / ecu);
}

double Concreto::eps_reta_b_pmilh() const {
    return std::min(eps_c2_pmilh(), eps_cu_pmilh());
}

double strain_pmilh(
    double s, double x_LN, double h_inc, double d_inc_,
    double eps_c2, double eps_cu, double pivo_c_rel)
{
    const double x_lim_2_3 = eps_cu / (eps_cu + EPS_SU) * d_inc_;
    if (x_LN <= x_lim_2_3) {
        // Dominio 2: pivo A
        return EPS_SU * (x_LN - s) / (d_inc_ - x_LN);
    }
    if (x_LN <= h_inc) {
        // Dominio 3/4/4a: pivo B
        return eps_cu * (x_LN - s) / x_LN;
    }
    // Dominio 5: pivo C a (eps_cu - eps_c2)/eps_cu * h da face. Em C90 a
    // norma da eps_c2 > eps_cu: usa-se o menor (continuidade em x = h).
    return std::min(eps_c2, eps_cu) * (x_LN - s) / (x_LN - pivo_c_rel * h_inc);
}

double sigma_concreto(double eps, double pico, double eps_c2, double n_par)
{
    // Tracao ou nao-comprimido -> 0
    if (eps <= 0.0) return 0.0;
    // Patamar plastico (mantido alem de eps_cu, como no Python)
    if (eps > eps_c2) return pico;
    // Parabolica: sigma = pico * (1 - (1 - eps/eps_c2)^n)
    const double r = 1.0 - eps / eps_c2;
    return pico * (1.0 - std::pow(r, n_par));
}

double sigma_aco(double eps, double fyd, double Es, double eps_yd) {
    const double abs_eps = std::abs(eps);
    if (abs_eps <= eps_yd) {
        return eps / 1000.0 * Es;
    }
    return (eps > 0 ? 1.0 : -1.0) * fyd;
}

}  // namespace fco
