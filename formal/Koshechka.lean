import Mathlib.Analysis.SpecialFunctions.Trigonometric.Basic
import Mathlib.Tactic
namespace Koshechka
noncomputable section

def landing (y v T t : ℝ) : ℝ :=
  ((v*T+2*y)/T^3)*t^3 - ((2*v*T+3*y)/T^2)*t^2 + v*t + y

def landingVelocity (y v T t : ℝ) : ℝ :=
  3*((v*T+2*y)/T^3)*t^2 - 2*((2*v*T+3*y)/T^2)*t + v

theorem landing_initial (y v T : ℝ) :
    landing y v T 0 = y ∧ landingVelocity y v T 0 = v := by
  simp [landing, landingVelocity]

theorem landing_derivative (y v T t : ℝ) :
    HasDerivAt (landing y v T) (landingVelocity y v T t) t := by
  unfold landing landingVelocity
  convert (((((hasDerivAt_id t).pow 3).const_mul ((v*T+2*y)/T^3)).sub
    (((hasDerivAt_id t).pow 2).const_mul ((2*v*T+3*y)/T^2))).add
    ((hasDerivAt_id t).const_mul v)).add_const y using 1 <;> (simp only [id_eq]; ring)

theorem landing_final (y v T : ℝ) (hT : 0 < T) :
    landing y v T T = 0 ∧ landingVelocity y v T T = 0 := by
  have hn : T ≠ 0 := ne_of_gt hT
  constructor <;> simp only [landing, landingVelocity] <;> field_simp <;> ring

/-- Chord cost for two unit vectors. -/
theorem chord_linear (x y u v : ℝ) (hp : x^2+y^2=1) (hq : u^2+v^2=1) :
    (x-u)^2+(y-v)^2 = 2-2*(x*u+y*v) := by nlinarith

/-- Rotate each phase by its prescribed cross offset before summing. -/
theorem cross_linear (x y : Fin 4 → ℝ) (u v : ℝ)
    (hp : ∀ i, (x i)^2+(y i)^2=1) (hq : u^2+v^2=1) :
    (∑ i, ((x i-u)^2+(y i-v)^2)) =
      8-2*((∑ i, x i)*u+(∑ i, y i)*v) := by
  simp_rw [chord_linear _ _ _ _ (hp _) hq]
  simp only [Fin.sum_univ_succ]
  ring

theorem resultant_minimum (C S r u v : ℝ) (hr : 0 < r)
    (hn : C^2+S^2=r^2) (hu : u^2+v^2=1) :
    8-2*r ≤ 8-2*(C*u+S*v) := by
  have h := add_nonneg (sq_nonneg (C-r*u)) (sq_nonneg (S-r*v))
  have hmul : r^2*(u^2+v^2)=r^2 := by rw [hu]; ring
  have hbound : 0 ≤ 2*r*(r-(C*u+S*v)) := by nlinarith
  have : 0 ≤ r-(C*u+S*v) := nonneg_of_mul_nonneg_right hbound (by positivity : 0 < 2*r)
  linarith

theorem normalized_attains (C S r : ℝ) (hr : 0 < r) (hn : C^2+S^2=r^2) :
    (C/r)^2+(S/r)^2=1 ∧ C*(C/r)+S*(S/r)=r := by
  have hne : r ≠ 0 := ne_of_gt hr
  constructor <;> field_simp <;> nlinarith

theorem degenerate_cross (u v : ℝ) : 8-2*((0:ℝ)*u+0*v)=8 := by ring

theorem phase_unit (a : ℝ) : (Real.cos a)^2+(Real.sin a)^2=1 := by
  nlinarith [Real.sin_sq_add_cos_sq a]

#print axioms landing_initial
#print axioms landing_derivative
#print axioms landing_final
#print axioms cross_linear
#print axioms resultant_minimum
#print axioms normalized_attains
#print axioms degenerate_cross
#print axioms phase_unit
end
end Koshechka
