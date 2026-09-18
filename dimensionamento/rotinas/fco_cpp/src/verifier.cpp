#include "verifier.h"
#include "solver.h"
#include <cmath>
#include <cstdio>
#include <limits>
#include <algorithm>

namespace fco {

double Nd_max_kn(const SecaoRetangular& s, const Concreto& c, const Aco& a) {
    // Reta b da Figura 17.1: encurtamento uniforme eps_c2 (FCO-01, FCO-05).
    const double eps_b = c.eps_reta_b_pmilh();
    const double sig_c = sigma_concreto(eps_b, c.pico_kncm2(), c.eps_c2_pmilh(), c.n_parabola());
    const double sig_s = sigma_aco(eps_b, a.fyd_kncm2(), a.Es_kncm2, a.eps_yd_pmilh());
    const double As = s.As_total_cm2();
    return sig_c * (s.Ac_cm2() - As) + sig_s * As;
}

double Nd_min_kn(const SecaoRetangular& s, const Aco& a) {
    return -a.fyd_kncm2() * s.As_total_cm2();
}

namespace {

// OK so com MR >= MS (17.2.1): razao >= 1, sem folga (FCO-11).
const char* status_razao(double razao) {
    return (razao >= 1.0) ? "OK" : "NAO_VERIFICA";
}

std::string formatar(const char* fmt, double a, double b) {
    char buf[300];
    std::snprintf(buf, sizeof(buf), fmt, a, b);
    return buf;
}

const char* MSG_ORIGEM_FORA =
    "Com Nd = %.1f kN nem o momento nulo é resistido: o centro plástico "
    "da seção não coincide com o centroide e a envoltória resistente para "
    "esse Nd não contém a origem.";

// (N, Mx, My) com deformacao uniforme eps (por mil) na secao inteira.
Esforcos esforcos_uniformes(const SecaoRetangular& s, const Concreto& c,
                            const Aco& a, double eps) {
    const double sc = sigma_concreto(eps, c.pico_kncm2(), c.eps_c2_pmilh(), c.n_parabola());
    const double ss = sigma_aco(eps, a.fyd_kncm2(), a.Es_kncm2, a.eps_yd_pmilh());
    if (s.barras.empty()) return {sc * s.Ac_cm2(), 0.0, 0.0};
    double As = 0.0, Sx = 0.0, Sy = 0.0;
    for (const auto& b : s.barras) {
        As += b.area_cm2;
        Sx += b.area_cm2 * b.y_cm;
        Sy += b.area_cm2 * b.x_cm;
    }
    return {sc * (s.Ac_cm2() - As) + ss * As, (ss - sc) * Sx, (ss - sc) * Sy};
}

// O ponto (Nd, 0, 0) esta dentro da envoltoria resistente com N = Nd?
// Ponto interior C: estado uniforme com N = Nd. Se C != 0, a origem esta
// dentro se e so se o raio que parte dela no sentido oposto a C encontra a
// envoltoria (convexidade). Mesmo algoritmo do Python (_origem_dentro).
bool origem_dentro(const SecaoRetangular& s, const Concreto& c, const Aco& a,
                   double Nd, int n_grid) {
    const double eps_b = c.eps_reta_b_pmilh();
    const double N_lo = esforcos_uniformes(s, c, a, -EPS_SU).N_kn;
    const double N_hi = esforcos_uniformes(s, c, a, eps_b).N_kn;
    if (!(N_lo < Nd && Nd < N_hi)) return true;
    auto fN = [&](double e) { return esforcos_uniformes(s, c, a, e).N_kn - Nd; };
    const double eps_N = brentq(fN, -EPS_SU, eps_b, 1e-12,
                                4.0 * std::numeric_limits<double>::epsilon(), 100);
    const Esforcos C = esforcos_uniformes(s, c, a, eps_N);
    const double escala = std::max(std::abs(Nd), Nd_max_kn(s, c, a))
                          * std::max(s.base_cm, s.altura_cm);
    if (std::hypot(C.Mx_kncm, C.My_kncm) <= 1e-9 * escala) return true;
    try {
        solve_direcao(s, c, a, Nd, std::atan2(-C.My_kncm, -C.Mx_kncm), n_grid);
    } catch (const SolverError&) {
        return false;
    }
    return true;
}

}  // namespace

VerifResult verificar_fco(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double Nd_kn, double Mxd_kncm, double Myd_kncm, int n_grid)
{
    VerifResult r;
    const double nan = std::numeric_limits<double>::quiet_NaN();
    r.razao = -1.0;
    r.alpha_rad = nan;
    r.x_LN_cm = nan;
    r.MRx_kncm = nan;
    r.MRy_kncm = nan;
    r.MR_kncm = nan;

    const double Nd_max = Nd_max_kn(secao, concreto, aco);
    const double Nd_min = Nd_min_kn(secao, aco);
    if (Nd_kn > Nd_max) {
        r.status = "FORA_RANGE";
        r.mensagem = formatar("Nd = %.1f kN > Nd,máx = %.1f kN (compressão uniforme).", Nd_kn, Nd_max);
        return r;
    }
    if (Nd_kn < Nd_min) {
        r.status = "FORA_RANGE";
        r.mensagem = formatar("Nd = %.1f kN < Nd,mín = %.1f kN (tração uniforme).", Nd_kn, Nd_min);
        return r;
    }

    const double Md_total = std::hypot(Mxd_kncm, Myd_kncm);
    if (Md_total < 1e-6) {
        r.status = "OK";
        r.razao = std::numeric_limits<double>::infinity();
        r.alpha_rad = 0.0;
        return r;
    }

    // Direcao com sinal (FCO-03).
    const double theta_d = std::atan2(Myd_kncm, Mxd_kncm);
    try {
        if (!origem_dentro(secao, concreto, aco, Nd_kn, n_grid)) {
            r.status = "NAO_VERIFICA";
            r.razao = 0.0;
            r.mensagem = formatar(MSG_ORIGEM_FORA, Nd_kn, 0.0);
            return r;
        }
        const AlphaResult ar = solve_direcao(secao, concreto, aco, Nd_kn, theta_d, n_grid);
        const double Mr = std::hypot(ar.Mx_kncm, ar.My_kncm);
        const double razao = Mr / Md_total;
        r.status = status_razao(razao);
        r.razao = razao;
        r.alpha_rad = ar.alpha;
        r.x_LN_cm = ar.x_LN;
        r.MRx_kncm = std::abs(ar.Mx_kncm);
        r.MRy_kncm = std::abs(ar.My_kncm);
        r.MR_kncm = Mr;
        r.uniaxial = ar.uniaxial;
    } catch (const SolverError& ex) {
        r.status = "NAO_CONVERGIU";
        r.razao = -1.0;
        r.mensagem = ex.what();
    }
    return r;
}

RadialResult razao_dc_radial(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double Nd_kn, double Mxd_kncm, double Myd_kncm, int n_grid)
{
    RadialResult r;
    const double nan = std::numeric_limits<double>::quiet_NaN();
    const double inf = std::numeric_limits<double>::infinity();
    const double MS = std::hypot(Mxd_kncm, Myd_kncm);
    const double Nrd_max = Nd_max_kn(secao, concreto, aco);
    const double Nrd_min = Nd_min_kn(secao, aco);

    // Caso compressao/tracao quase pura
    if (MS < 1e-6) {
        if (std::abs(Nd_kn) < 1e-6) {
            r.status = "OK"; r.razao_dc = 0.0; r.lambda = inf;
            return r;
        }
        const double lam = (Nd_kn > 0) ? Nrd_max / Nd_kn : Nrd_min / Nd_kn;
        r.status = (lam >= 1.0) ? "OK" : "NAO_VERIFICA";
        r.razao_dc = (lam > 0) ? 1.0 / lam : inf;
        r.lambda = lam;
        return r;
    }

    // Direcao com sinal (FCO-03); flexao normal via LN paralela ao eixo (FCO-18).
    const double theta_d = std::atan2(Myd_kncm, Mxd_kncm);
    double lam_axial_max;
    if (Nd_kn > 1e-6) lam_axial_max = Nrd_max / Nd_kn;
    else if (Nd_kn < -1e-6) lam_axial_max = Nrd_min / Nd_kn;
    else lam_axial_max = inf;

    auto g = [&](double lam) -> double {
        const double Nd_t = lam * Nd_kn;
        if (Nd_t > Nrd_max - 1e-3 || Nd_t < Nrd_min + 1e-3) {
            return -lam * MS - 1.0;
        }
        try {
            if (!origem_dentro(secao, concreto, aco, Nd_t, n_grid)) {
                return -lam * MS - 1.0;  // nem (lam*Nd, 0, 0) e resistido
            }
            const AlphaResult ar = solve_direcao(secao, concreto, aco, Nd_t, theta_d, n_grid);
            const double MR = std::hypot(ar.Mx_kncm, ar.My_kncm);
            return MR / lam - MS;
        } catch (const SolverError&) {
            return nan;
        }
    };

    const double g1 = g(1.0);
    if (!std::isfinite(g1)) {
        r.status = "NAO_CONVERGIU"; r.razao_dc = nan; r.lambda = nan;
        r.mensagem = "g(1.0) não avaliável";
        return r;
    }

    double lo = 0.0, hi = 0.0;
    if (g1 > 0) {
        lo = 1.0;
        hi = std::min(2.0, std::isfinite(lam_axial_max) ? 0.95 * lam_axial_max : 100.0);
        if (hi <= lo) {
            r.status = "OK"; r.razao_dc = 1.0 / lam_axial_max; r.lambda = lam_axial_max;
            return r;
        }
        bool found = false;
        for (int i = 0; i < 20; ++i) {
            const double gh = g(hi);
            if (std::isfinite(gh) && gh < 0) { found = true; break; }
            const double new_hi = std::isfinite(lam_axial_max)
                ? std::min(hi * 1.5, 0.95 * lam_axial_max)
                : hi * 1.5;
            if (new_hi <= hi * 1.001) {
                r.status = "OK"; r.razao_dc = 1.0 / hi; r.lambda = hi;
                return r;
            }
            if (std::isfinite(gh)) lo = hi;  // so avanca lo onde g(lo) > 0 e finito
            hi = new_hi;
        }
        if (!found) {
            r.status = "NAO_CONVERGIU"; r.razao_dc = nan; r.lambda = nan;
            r.mensagem = "Não achou bracketing superior";
            return r;
        }
    } else {
        lo = 0.5; hi = 1.0;
        bool found = false;
        for (int i = 0; i < 20; ++i) {
            const double gl = g(lo);
            if (std::isfinite(gl) && gl > 0) { found = true; break; }
            lo *= 0.5;
            if (lo < 1e-4) {
                r.status = "NAO_CONVERGIU"; r.razao_dc = nan; r.lambda = nan;
                r.mensagem = "Não achou bracketing inferior";
                return r;
            }
        }
        if (!found) {
            r.status = "NAO_CONVERGIU"; r.razao_dc = nan; r.lambda = nan;
            r.mensagem = "Não achou bracketing inferior (esgotou)";
            return r;
        }
    }

    try {
        const double lam_sol = brentq(g, lo, hi, 1e-3, 1e-4, 50);
        r.status = (lam_sol >= 1.0) ? "OK" : "NAO_VERIFICA";
        r.razao_dc = 1.0 / lam_sol;
        r.lambda = lam_sol;
    } catch (const SolverError& ex) {
        r.status = "NAO_CONVERGIU"; r.razao_dc = nan; r.lambda = nan;
        r.mensagem = ex.what();
    }
    return r;
}

}  // namespace fco
