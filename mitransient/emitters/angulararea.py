# from __future__ import annotations  # Delayed parsing of type annotations

import drjit as dr
import mitsuba as mi
from mitsuba import Log, LogLevel

from typing import Tuple


class AngularAreaLight(mi.Emitter):
    def __init__(self, props: mi.Properties):
        super().__init__(props)
        self.radiance: mi.Texture = props.get('radiance')
        cutoff_angle: mi.Float = props.get('cutoff_angle', 10)
        self.cutoff_angle: mi.Float = dr.deg2rad(cutoff_angle)
        beam_width: mi.Float = props.get('beam_width', cutoff_angle)
        self.beam_width: mi.Float = dr.deg2rad(beam_width)
        difference: mi.Float = (self.cutoff_angle - self.beam_width)
        if difference == 0.0:
            self.inv_trasnsition_width: mi.Float = dr.inf
        else:
            self.inv_trasnsition_width: mi.Float = 1.0 / difference
        self.cos_cutoff_angle: mi.Float = dr.cos(self.cutoff_angle)
        self.cos_beam_width: mi.Float = dr.cos(self.beam_width)

        assert dr.all(self.cutoff_angle >= self.beam_width)

        self.m_flags = mi.EmitterFlags.Surface


    """
    def sample_wavelengths(self, si: mi.SurfaceInteraction3f, sample: mi.Float, active: mi.Mask) -> Tuple[mi.Wavelength, mi.Spectrum]:
        raise NotImplementedError


    def pdf_wavelengths():
        raise NotImplementedError
    """


    def sample_ray(self, time: mi.Float, sample1: mi.Float, sample2: mi.Float, sample3: mi.Float, active: mi.Bool) -> Tuple[mi.Ray3f, mi.Spectrum]:
        raise NotImplementedError


    def _fallof_curve(self, d: mi.Vector3f) -> mi.Float:
        local_dir: mi.Vector3f = dr.normalize(d)
        cos_theta: mi.Float = local_dir.z
        beam_res: mi.Float = dr.select(
            cos_theta >= self.cos_beam_width, 1.0,
            (self.cutoff_angle - dr.acos(cos_theta)) * self.inv_trasnsition_width
        )

        return dr.select(cos_theta > self.cos_cutoff_angle, beam_res, 0.0)


    def sample_direction(self, ref: mi.Interaction3f, sample: mi.Point2f, active: mi.Bool) -> Tuple[mi.DirectionSample3f, mi.Spectrum]:
        # Sample position in shape and weight by the square distance (solid angle)
        ds: mi.DirectionSample3f = self.shape().sample_direction(ref, sample, active)
        active &= dr.dot(ds.d, ds.n) > 0.0 & dr.neq(ds.pdf, 0.0)
        si: mi.SurfaceInteraction3f = mi.SurfaceInteraction3f(ds, ref.wavelengths)

        # Evaluate emitted radiance & fallof profile
        falloff: mi.Float = self._fallof_curve(ds.d)
        active &= falloff > 0.0

        # Weight radiance by falloff, pdf and cosine (included in pdf)
        spec = self.radiance.eval(si, active) * falloff / ds.pdf
 
        return ds, spec & active


    def pdf_direction(self, ref: mi.Interaction3f, ds: mi.DirectionSample3f, active: mi.Bool) -> mi.Float:
        dp: mi.Float = dr.dot(ds.d, ds.n)
        active &= dp > 0.0
        
        value = self.shape().pdf_direction(ref, ds, active)

        return dr.select(active, value, 0.0)


    def eval_direction(self, ref: mi.Interaction3f, ds: mi.DirectionSample3f, active: mi.Bool) -> mi.Spectrum:
        dp: mi.Float = dr.dot(ds.d, ds.n)
        active &= dp > 0.0

        # Evaluate emitted radiance & fallof profile
        falloff: mi.Float = self._fallof_curve(ds.d)
        active &= falloff > 0.0
        
        # Weight radiance by falloff and cosine
        si: mi.SurfaceInteraction3f = mi.SurfaceInteraction3f(ds, ref.wavelengths)
        spec = self.radiance.eval(si, active) * falloff * dp

        return dr.select(active, spec, 0.0)


    def sample_position(self, time: mi.Float, sample: mi.Point2f, active: mi.Bool) -> Tuple[mi.PositionSample3f, mi.Float]:
        raise NotImplementedError


    def pdf_position(self, ps: mi.PositionSample3f, active: mi.Bool) -> mi.Float:
        raise NotImplementedError


    def eval(self, si: mi.SurfaceInteraction3f, active: mi.Bool) -> mi.Spectrum:
        # Evaluate emitted radiance & fallof profile
        falloff: mi.Float = self._fallof_curve(si.wi)
        spec = self.radiance.eval(si, active) * falloff
        active &= falloff > 0.0

        active &= mi.Frame3f.cos_theta(si.wi) > 0

        return spec & active

    def traverse(self, callback: mi.TraversalCallback):
        # NOTE: all the parameters are set as NonDifferentiable by default
        super().traverse(callback)
        callback.put_parameter("radiance", self.radiance, mi.ParamFlags.NonDifferentiable)
        callback.put_parameter("cutoff_angle", self.cutoff_angle, mi.ParamFlags.NonDifferentiable)
        callback.put_parameter("beam_width", self.beam_width, mi.ParamFlags.NonDifferentiable)

    
    def parameters_changed(self, keys):
        super().parameters_changed(keys)

    def to_string(self):
        string = f"{type(self).__name__}[\n"
        string += f"  radiance = {self.radiance},"
        string += f"  cutoff_angle = {dr.rad2deg(self.cutoff_angle)},"
        string += f"  beam_width = {dr.rad2deg(self.beam_width)},"
        string += f"]"
        return string
    
mi.register_emitter('angulararea', lambda props: AngularAreaLight(props))