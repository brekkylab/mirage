// ========= Copyright 2026 @ Strukto.AI All Rights Reserved. =========
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// ========= Copyright 2026 @ Strukto.AI All Rights Reserved. =========

import { describe, expect, it } from 'vitest'
import { traceAssignment, traceCommand } from './xtrace.ts'

const text = (b: Uint8Array): string => new TextDecoder().decode(b)

describe('xtrace rendering', () => {
  it('renders plain words', () => {
    expect(text(traceCommand(['echo', 'hi']))).toBe('+ echo hi\n')
  })

  it('quotes words with spaces', () => {
    expect(text(traceCommand(['echo', 'a b']))).toBe("+ echo 'a b'\n")
  })

  it('quotes the empty word', () => {
    expect(text(traceCommand(['echo', '']))).toBe("+ echo ''\n")
  })

  it('keeps safe specials unquoted', () => {
    expect(text(traceCommand(['grep', '-c', 'a=b']))).toBe('+ grep -c a=b\n')
  })

  it('renders a plain assignment', () => {
    expect(text(traceAssignment('x', '5', false))).toBe('+ x=5\n')
  })

  it('renders an append assignment', () => {
    expect(text(traceAssignment('x', 'y', true))).toBe('+ x+=y\n')
  })

  it('renders an empty value bare', () => {
    expect(text(traceAssignment('x', '', false))).toBe('+ x=\n')
  })

  it('quotes an assignment value with spaces', () => {
    expect(text(traceAssignment('x', 'a b', false))).toBe("+ x='a b'\n")
  })
})
