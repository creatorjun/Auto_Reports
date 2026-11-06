// frontend/src/application/services/kernelSelection.ts
import type { KernelSelection, KernelTarget } from '@/domain/KernelCve'

export function resolveKernelSelection(targets: KernelTarget[], saved: Partial<KernelSelection> | null): KernelSelection | null {
  const target = targets.find((item) => item.available && item.id === saved?.target)
    ?? targets.find((item) => item.available)
  if (!target) return null
  const sameTarget = target.id === saved?.target
  const pkg = sameTarget && saved?.package && target.packages.includes(saved.package) ? saved.package : target.packages[0]
  const architecture = sameTarget && saved?.architecture && target.architectures.includes(saved.architecture)
    ? saved.architecture : target.architectures[0]
  if (!pkg || !architecture) return null
  const sameBuild = sameTarget && saved?.package === pkg && saved.architecture === architecture
  const version = sameBuild && typeof saved.version === 'string' && saved.version.length <= 128 ? saved.version.trim() : ''
  return { target: target.id, package: pkg, architecture, version }
}
