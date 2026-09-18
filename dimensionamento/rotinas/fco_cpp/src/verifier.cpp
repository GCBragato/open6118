#include "verifier.h"
#include "solver.h"
#include <cmath>
#include <limits>
#include <algorithm>

namespace fco {

double Nd_max_kn(const SecaoRetangular& s, const Concreto& c, const Aco& a) {
    const double Ac_liq = s.Ac_cm2() - s.As_total_cm2();
    return ALPHA_C * c.fcd_kncm2() * Ac_liq + a.fyd_kncm2() * s.As_total_cm2();
}

double Nd_min_kn(const SecaoRetangular& s, const Aco& a) {
    return -a.fyd_kncm2() * s.As_total_cm2();
}

static VerifResult verificar_uniaxial(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double Nd_kn, double Md_kncm, double alpha, int n_grid)
{
    VerifResult r;
    try {
        const double x_LN = solve_x_LN(secao, concreto, aco, alpha, Nd_kn, n_grid);
        Esforcos e = esforcos_resistentes(secao, concreto, aco, alpha, x_LN, n_grid);
        const double Mr = std::hypot(e.Mx_kncm, e.My_kncm);
        const double razao = (std::abs(Md_kncm) > 0) ? Mr / std::abs(Md_kncm) : std::numeric_limits<double>::infinity();
        r.status = (razao >= 0.99) ? "OK" : "NAO_VERIFICA";
        r.razao = razao;
        r.alpha_rad = alpha;
        r.x_LN_cm = x_LN;
        r.MRx_kncm = std::abs(e.Mx_kncm);
        r.MRy_kncm = std::abs(e.My_kncm);
        r.MR_kncm = Mr;
    } catch (const SolverError& ex) {
        r.status = "NAO_CONVERGIU";
        r.razao = -1.0;
        r.mensagem = ex.what();
    }
    return r;
}

VerifResult verificar_fco(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double Nd_kn, double Mxd_kncm, double Myd_kncm, int n_grid)
{
    VerifResult r;
    const double Nd_max = Nd_max_kn(secao, concreto, aco);
    const double Nd_min = Nd_min_kn(secao, aco);
    if (Nd_kn > Nd_max) {
        r.status = "FORA_RANGE"; r.razao = -1.0;
        r.mensagem = "Nd > Nd_max (compressao pura)";
        return r;
    }
    if (Nd_kn < Nd_min) {
        r.status = "FORA_RANGE"; r.razao = -1.0;
        r.mensagem = "Nd < Nd_min (tracao pura)";
        return r;
    }

    const double Md_total = std::hypot(Mxd_kncm, Myd_kncm);
    if (Md_total < 1e-6) {
        r.status = "OK";
        r.razao = std::numeric_limits<double>::infinity();
        r.alpha_rad = 0.0;
        r.x_LN_cm = std::nan("");
        return r;
    }

    if (std::abs(Myd_kncm) / Md_total < 1e-6) {
        return verificar_uniaxial(secao, concreto, aco, Nd_kn, std::abs(Mxd_kncm), 0.0, n_grid);
    }
    if (std::abs(Mxd_kncm) / Md_total < 1e-6) {
        return verificar_uniaxial(secao, concreto, aco, Nd_kn, std::abs(Myd_kncm), -1.5707963267948966, n_grid);
    }

    const double theta_d = std::atan2(std::abs(Myd_kncm), std::abs(Mxd_kncm));

    try {
        AlphaResult ar = solve_alpha(secao, concreto, aco, Nd_kn, theta_d, n_grid);
        Esforcos e = esforcos_resistentes(secao, concreto, aco, ar.alpha, ar.x_LN, n_grid);
        const double Mr = std::hypot(e.Mx_kncm, e.My_kncm);
        const double razao = Mr / Md_total;
        r.status = (razao >= 0.99) ? "OK" : "NAO_VERIFICA";
        r.razao = razao;
        r.alpha_rad = ar.alpha;
        r.x_LN_cm = ar.x_LN;
        r.MRx_kncm = std::abs(e.Mx_kncm);
        r.MRy_kncm = std::abs(e.My_kncm);
        r.MR_kncm = Mr;
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
    const double MS = std::hypot(Mxd_kncm, Myd_kncm);
    const double Nrd_max = Nd_max_kn(secao, concreto, aco);
    const double Nrd_min = Nd_min_kn(secao, aco);

    // Caso compressao/tracao quase pura
    if (MS < 1e-6) {
        if (std::abs(Nd_kn) < 1e-6) {
            r.status = "OK"; r.razao_dc = 0.0; r.lambda = std::numeric_limits<double>::infinity();
            return r;
        }
        const double lam = (Nd_kn > 0) ? Nrd_max / Nd_kn : Nrd_min / Nd_kn;
        r.status = (lam >= 1.0) ? "OK" : "NAO_VERIFICA";
        r.razao_dc = (lam > 0) ? 1.0 / lam : std::numeric_limits<double>::infinity();
        r.lambda = lam;
        return r;
    }

    const double theta_d = std::atan2(std::abs(Myd_kncm), std::abs(Mxd_kncm));
    double lam_axial_max;
    if (Nd_kn > 1e-6) lam_axial_max = Nrd_max / Nd_kn;
    else if (Nd_kn < -1e-6) lam_axial_max = Nrd_min / Nd_kn;
    else lam_axial_max = std::numeric_limits<double>::infinity();

    auto g = [&](double lam) -> double {
        const double Nd_t = lam * Nd_kn;
        if (Nd_t > Nrd_max - 1e-3 || Nd_t < Nrd_min + 1e-3) {
            return -lam * MS - 1.0;
        }
        try {
            AlphaResult ar = solve_alpha(secao, concreto, aco, Nd_t, theta_d, n_grid);
            Esforcos e = esforcos_resistentes(secao, concreto, aco, ar.alpha, ar.x_LN, n_grid);
            const double MR = std::hypot(e.Mx_kncm, e.My_kncm);
            return MR / lam - MS;
        } catch (const SolverError&) {
            return std::nan("");
        }
    };

    const double g1 = g(1.0);
    if (!std::isfinite(g1)) {
        r.status = "NAO_CONVERGIU"; r.razao_dc = std::nan(""); r.lambda = std::nan("");
        r.mensagem = "g(1.0) nao avaliavel";
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
            lo = hi; hi = new_hi;
        }
        if (!found) {
            r.status = "NAO_CONVERGIU"; r.razao_dc = std::nan(""); r.lambda = std::nan("");
            r.mensagem = "Nao achou bracketing superior";
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
                r.status = "NAO_CONVERGIU"; r.razao_dc = std::nan(""); r.lambda = std::nan("");
                r.mensagem = "Nao achou bracketing inferior";
                return r;
            }
        }
        if (!found) {
            r.status = "NAO_CONVERGIU"; r.razao_dc = std::nan(""); r.lambda = std::nan("");
            r.mensagem = "Nao achou bracketing inferior (esgotou)";
            return r;
        }
    }

    try {
        const double lam_sol = brentq(g, lo, hi, 1e-3, 1e-4, 50);
        r.status = (lam_sol >= 1.0) ? "OK" : "NAO_VERIFICA";
        r.razao_dc = 1.0 / lam_sol;
        r.lambda = lam_sol;
    } catch (const SolverError& ex) {
        r.status = "NAO_CONVERGIU"; r.razao_dc = std::nan(""); r.lambda = std::nan("");
        r.mensagem = ex.what();
    }
    return r;
}

}  // namespace fco
