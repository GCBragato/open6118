#include "solver.h"
#include <algorithm>
#include <cmath>
#include <limits>
#include <vector>

namespace fco {

namespace {

constexpr double PI = 3.14159265358979323846;
constexpr double EPS_ALPHA = 1e-3;          // folga nas pontas da faixa do quadrante
constexpr double PASSO_ALPHA = PI / 16.0;   // passo da busca no circulo inteiro
constexpr double TOL_UNIAXIAL = 1e-6;       // |M perpendicular|/|M| = flexao normal

// Diferenca de angulos em (-pi, pi] (sem mexer se ja estiver).
double wrap_pi(double a) {
    if (a > PI) a -= 2.0 * PI;
    else if (a <= -PI) a += 2.0 * PI;
    return a;
}

int sinal(double v) { return (v > 0.0) - (v < 0.0); }

}  // namespace

// Porte de scipy/optimize/Zeros/brentq.c (mesma sequencia de passos).
double brentq(
    const std::function<double(double)>& f,
    double xa, double xb,
    double xtol, double rtol, int maxiter)
{
    double xpre = xa, xcur = xb;
    double xblk = 0.0, fblk = 0.0, spre = 0.0, scur = 0.0;
    double fpre = f(xpre);
    double fcur = f(xcur);
    if (fpre == 0.0) return xpre;
    if (fcur == 0.0) return xcur;
    if (std::signbit(fpre) == std::signbit(fcur)) {
        throw SolverError("brentq: f(a) e f(b) com o mesmo sinal.");
    }
    for (int it = 0; it < maxiter; ++it) {
        if (fpre != 0.0 && fcur != 0.0 && std::signbit(fpre) != std::signbit(fcur)) {
            xblk = xpre;
            fblk = fpre;
            spre = scur = xcur - xpre;
        }
        if (std::fabs(fblk) < std::fabs(fcur)) {
            xpre = xcur;
            xcur = xblk;
            xblk = xpre;

            fpre = fcur;
            fcur = fblk;
            fblk = fpre;
        }

        const double delta = (xtol + rtol * std::fabs(xcur)) / 2.0;
        const double sbis = (xblk - xcur) / 2.0;
        if (fcur == 0.0 || std::fabs(sbis) < delta) {
            return xcur;
        }

        if (std::fabs(spre) > delta && std::fabs(fcur) < std::fabs(fpre)) {
            double stry;
            if (xpre == xblk) {
                // interpolacao
                stry = -fcur * (xcur - xpre) / (fcur - fpre);
            } else {
                // extrapolacao
                const double dpre = (fpre - fcur) / (xpre - xcur);
                const double dblk = (fblk - fcur) / (xblk - xcur);
                stry = -fcur * (fblk * dblk - fpre * dpre)
                    / (dblk * dpre * (fblk - fpre));
            }
            if (2.0 * std::fabs(stry) < std::min(std::fabs(spre), 3.0 * std::fabs(sbis) - delta)) {
                // passo curto bom
                spre = scur;
                scur = stry;
            } else {
                // bissecao
                spre = sbis;
                scur = sbis;
            }
        } else {
            // bissecao
            spre = sbis;
            scur = sbis;
        }

        xpre = xcur;
        fpre = fcur;
        if (std::fabs(scur) > delta) {
            xcur += scur;
        } else {
            xcur += (sbis > 0.0 ? delta : -delta);
        }
        fcur = f(xcur);
    }
    throw SolverError("brentq: não convergiu no número máximo de iterações.");
}

double solve_x_LN(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double alpha, double Nd_kn, int n_grid,
    int n_sample)
{
    const InclResult ir = h_inc_yp_max(secao, alpha);
    const double h_inc = ir.h_inc;
    const double x_min = 1e-3;
    double x_max = 5.0 * h_inc;

    auto residual = [&](double x) -> double {
        Esforcos r = esforcos_resistentes(secao, concreto, aco, alpha, x, n_grid);
        return r.N_kn - Nd_kn;
    };

    std::vector<double> xs(n_sample), Ns(n_sample);
    // Mesmos pontos de numpy.linspace: i*passo + inicio, ultimo = fim.
    auto amostrar = [&]() {
        const double passo = (x_max - x_min) / (n_sample - 1);
        for (int i = 0; i < n_sample; ++i) {
            xs[i] = (i == n_sample - 1) ? x_max : i * passo + x_min;
            Ns[i] = residual(xs[i]);
        }
    };
    // Primeira troca de sinal (np.diff(np.sign(Ns)) != 0).
    auto primeira_troca = [&]() -> int {
        for (int i = 0; i < n_sample - 1; ++i) {
            if (sinal(Ns[i]) != sinal(Ns[i + 1])) return i;
        }
        return -1;
    };

    amostrar();
    int idx = primeira_troca();
    if (idx < 0) {
        x_max *= 4.0;
        amostrar();
        idx = primeira_troca();
        if (idx < 0) {
            if (Ns[n_sample - 1] < 0.0) {
                // FCO-05: dominio 5 so chega a reta b com x_LN -> infinito.
                double x_a = xs[n_sample - 1], r_a = Ns[n_sample - 1];
                const double fatores[4] = {1e2, 1e3, 1e4, 1e6};
                for (double fator : fatores) {
                    const double x_b = fator * h_inc;
                    const double r_b = residual(x_b);
                    if (r_b >= 0.0) {
                        return brentq(residual, x_a, x_b, 1e-4, 1e-6, 100);
                    }
                    x_a = x_b;
                    r_a = r_b;
                }
                if (r_a >= -1e-6 * std::max(1.0, std::abs(Nd_kn))) {
                    return x_a;  // compressao praticamente uniforme (reta b)
                }
            }
            throw SolverError(
                "Sem raiz para x_LN: Nd fora da faixa de N alcançada pelos domínios 2 a 5.");
        }
    }
    return brentq(residual, xs[idx], xs[idx + 1], 1e-4, 1e-6, 100);
}

AlphaResult solve_direcao(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double Nd_kn, double theta_d, int n_grid)
{
    const double nan = std::numeric_limits<double>::quiet_NaN();
    const double c_d = std::cos(theta_d);
    const double s_d = std::sin(theta_d);

    auto avaliar = [&](double alpha, double& x, double& Mx, double& My) {
        x = solve_x_LN(secao, concreto, aco, alpha, Nd_kn, n_grid);
        const Esforcos e = esforcos_resistentes(secao, concreto, aco, alpha, x, n_grid);
        Mx = e.Mx_kncm;
        My = e.My_kncm;
    };
    auto desvio = [&](double alpha) -> double {
        double x, Mx, My;
        avaliar(alpha, x, Mx, My);
        return wrap_pi(std::atan2(My, Mx) - theta_d);
    };
    auto desvio_seguro = [&](double alpha) -> double {
        try {
            return desvio(alpha);
        } catch (const SolverError&) {
            return nan;
        }
    };
    auto aceitar = [&](double alpha, AlphaResult& r) -> bool {
        double x, Mx, My;
        avaliar(alpha, x, Mx, My);
        if (std::abs(wrap_pi(std::atan2(My, Mx) - theta_d)) < 1e-2) {
            r.alpha = wrap_pi(alpha);
            r.x_LN = x;
            r.Mx_kncm = Mx;
            r.My_kncm = My;
            r.uniaxial = false;
            return true;
        }
        return false;
    };
    auto buscar = [&](double a, double b, AlphaResult& r) -> bool {
        try {
            const double raiz = brentq(desvio, a, b, 1e-4, 1e-5, 100);
            return aceitar(raiz, r);
        } catch (const SolverError&) {
            return false;
        }
    };

    // 1) Flexao normal: LN paralela ao eixo do momento.
    bool tem_fixo = false;
    double alpha_fixo = 0.0;
    if (std::abs(s_d) < TOL_UNIAXIAL) {
        tem_fixo = true;
        alpha_fixo = (c_d > 0.0) ? 0.0 : PI;
    } else if (std::abs(c_d) < TOL_UNIAXIAL) {
        tem_fixo = true;
        alpha_fixo = (s_d > 0.0) ? -PI / 2.0 : PI / 2.0;
    }
    if (tem_fixo) {
        double x, Mx, My;
        avaliar(alpha_fixo, x, Mx, My);
        const double MR = std::hypot(Mx, My);
        if (MR > 0.0 && Mx * c_d + My * s_d > 0.0
                && std::abs(Mx * s_d - My * c_d) <= TOL_UNIAXIAL * MR) {
            AlphaResult r;
            r.alpha = alpha_fixo;
            r.x_LN = x;
            r.Mx_kncm = Mx;
            r.My_kncm = My;
            r.uniaxial = true;
            return r;
        }
    }

    AlphaResult r;
    // 2) Faixa do quadrante de theta_d.
    const double q = std::floor(theta_d / (PI / 2.0));
    const double base = q * (PI / 2.0);
    const double a_lo = -base - PI / 2.0 + EPS_ALPHA;
    const double a_hi = -base - EPS_ALPHA;
    const double f_lo = desvio_seguro(a_lo);
    const double f_hi = desvio_seguro(a_hi);
    if (std::isfinite(f_lo) && std::isfinite(f_hi) && f_lo * f_hi <= 0.0) {
        if (buscar(a_lo, a_hi, r)) return r;
    }

    // 3) Circulo inteiro, a partir da LN perpendicular a direcao do momento.
    const double alpha0 = -theta_d;
    const double f0 = desvio_seguro(alpha0);
    if (f0 == 0.0 && aceitar(alpha0, r)) return r;
    const double sentido = !(f0 < 0.0) ? 1.0 : -1.0;
    for (double s : {sentido, -sentido}) {
        double a_ant = alpha0, f_ant = f0;
        for (int i = 1; i <= 16; ++i) {
            const double a_i = alpha0 + s * i * PASSO_ALPHA;
            const double f_i = desvio_seguro(a_i);
            if (std::isfinite(f_ant) && std::isfinite(f_i) && f_ant * f_i <= 0.0
                    && std::abs(f_ant) < PI / 2.0 && std::abs(f_i) < PI / 2.0) {
                if (buscar(std::min(a_ant, a_i), std::max(a_ant, a_i), r)) return r;
            }
            a_ant = a_i;
            f_ant = f_i;
        }
    }
    throw SolverError(
        "Solver alpha sem bracketing: nenhuma posição da LN leva o momento "
        "resistente à direção pedida.");
}

AlphaResult solve_alpha(
    const SecaoRetangular& secao,
    const Concreto& concreto,
    const Aco& aco,
    double Nd_kn, double theta_d, int n_grid)
{
    return solve_direcao(secao, concreto, aco, Nd_kn, theta_d, n_grid);
}

}  // namespace fco
