#pragma once

namespace fco {

constexpr double ALPHA_C = 0.85;

struct Concreto {
    double fck_mpa;
    double gama_c = 1.4;

    double fcd_kncm2() const;       // (fck/gamac) * 0.1
    double eps_c2_pmilh() const;    // 2.0 ate fck=50; senao formula
    double eps_cu_pmilh() const;    // 3.5 ate fck=50; senao formula
    double n_parabola() const;      // 2.0 ate fck=50; senao formula
};

struct Aco {
    double fyk_mpa = 500.0;
    double Es_kncm2 = 21000.0;  // 200 GPa
    double gama_s = 1.15;

    double fyd_kncm2() const { return (fyk_mpa / gama_s) * 0.1; }
    double eps_yd_pmilh() const { return fyd_kncm2() / Es_kncm2 * 1000.0; }
};

// Deformacao por mil em fibra a profundidade s (3 dominios via pivos A/B/C)
double strain_pmilh(
    double s, double x_LN, double h_inc, double d_inc,
    double eps_c2, double eps_cu);

// Parabola-retangulo NBR. Tracao -> 0. eps em por mil.
double sigma_concreto(
    double eps, double fcd, double eps_c2, double eps_cu, double n_par);

// Aco bilinear simetrico. eps em por mil. retorna sigma em kN/cm^2.
double sigma_aco(
    double eps, double fyd, double Es, double eps_yd);

}  // namespace fco
