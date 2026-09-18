#pragma once

namespace fco {

// Versao do kernel: 2 = correcoes da NBR 6118:2026 (eta_c, pivo C, patamar
// alem de eps_cu, sinal dos momentos, Nd_max com sigma_s(eps_c2), flexao
// normal no razao_dc_radial). O dispatcher Python so usa o C++ com >= 2.
constexpr int VERSAO_KERNEL = 2;

constexpr double ALPHA_C = 0.85;   // coeficiente 0,85 do pico 0,85*eta_c*fcd (Figura 8.2)
constexpr double EPS_SU = 10.0;    // alongamento-limite no pivo A (Figura 17.1), por mil
constexpr double FCK_MIN = 20.0;   // 8.2.1
constexpr double FCK_MAX = 90.0;   // 8.2.1

// Confere 20 <= fck <= 90 MPa (8.2.1); lanca std::invalid_argument fora disso.
void validar_fck(double fck_mpa);

struct Concreto {
    double fck_mpa;
    double gama_c = 1.4;

    double fcd_kncm2() const;         // (fck/gamac)/10
    double eta_c() const;             // 1 ate C40; (40/fck)^(1/3) acima
    double eps_c2_pmilh() const;      // 2.0 ate fck=50; senao formula
    double eps_cu_pmilh() const;      // 3.5 ate fck=50; senao formula
    double n_parabola() const;        // 2.0 ate fck=50; senao formula
    double pico_kncm2() const;        // 0,85*eta_c*fcd
    double pivo_c_rel() const;        // (eps_cu - eps_c2)/eps_cu, >= 0 (Figura 17.1)
    double eps_reta_b_pmilh() const;  // min(eps_c2, eps_cu): compressao uniforme
};

struct Aco {
    double fyk_mpa = 500.0;
    double Es_kncm2 = 21000.0;  // 210 GPa
    double gama_s = 1.15;

    double fyd_kncm2() const { return (fyk_mpa / gama_s) * 0.1; }
    double eps_yd_pmilh() const { return fyd_kncm2() / Es_kncm2 * 1000.0; }
};

// Deformacao por mil em fibra a profundidade s (Figura 17.1): pivo A
// (dominio 2), B (3, 4, 4a) e C a pivo_c_rel*h_inc da face (dominio 5).
// Sem armadura (d_inc = 0) nao ha dominio 2.
double strain_pmilh(
    double s, double x_LN, double h_inc, double d_inc,
    double eps_c2, double eps_cu, double pivo_c_rel);

// Parabola-retangulo NBR (pico = 0,85*eta_c*fcd). Tracao -> 0. Alem de
// eps_cu mantem o patamar (como o Python). eps em por mil.
double sigma_concreto(double eps, double pico, double eps_c2, double n_par);

// Aco bilinear simetrico. eps em por mil. retorna sigma em kN/cm^2.
double sigma_aco(
    double eps, double fyd, double Es, double eps_yd);

}  // namespace fco
