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

import type { PathSpec } from '../../../../types.ts'
import { scopePath } from '../scope.ts'
import { BINARY_OPS, UNARY_OPS } from './constants.ts'
import { applyBinary, applyUnary } from './operators.ts'
import { CondError } from './types.ts'
import type { CondContext } from './types.ts'

function evalOne(arg: string | PathSpec): boolean {
  return scopePath(arg) !== ''
}

function at(argv: (string | PathSpec)[], i: number): string | PathSpec {
  const v = argv[i]
  if (v === undefined) throw new CondError('argument expected')
  return v
}

async function evalTwo(ctx: CondContext, argv: (string | PathSpec)[]): Promise<boolean> {
  const first = scopePath(at(argv, 0))
  if (first === '!') return !evalOne(at(argv, 1))
  if (UNARY_OPS.has(first)) return applyUnary(ctx, first, at(argv, 1))
  throw new CondError(`${ctx.name}: ${first}: unary operator expected`)
}

async function evalThree(ctx: CondContext, argv: (string | PathSpec)[]): Promise<boolean> {
  const mid = scopePath(at(argv, 1))
  if (mid === '-a') {
    return evalOne(at(argv, 0)) && evalOne(at(argv, 2))
  }
  if (mid === '-o') {
    return evalOne(at(argv, 0)) || evalOne(at(argv, 2))
  }
  if (BINARY_OPS.has(mid)) {
    return applyBinary(ctx, at(argv, 0), mid, at(argv, 2))
  }
  const first = scopePath(at(argv, 0))
  if (first === '!') return !(await evalTwo(ctx, argv.slice(1)))
  if (first === '(' && scopePath(at(argv, 2)) === ')') {
    return evalOne(at(argv, 1))
  }
  throw new CondError(`${ctx.name}: ${mid}: binary operator expected`)
}

async function evalFour(ctx: CondContext, argv: (string | PathSpec)[]): Promise<boolean> {
  const first = scopePath(at(argv, 0))
  if (first === '!') return !(await evalThree(ctx, argv.slice(1)))
  if (first === '(' && scopePath(at(argv, 3)) === ')') {
    return evalTwo(ctx, argv.slice(1, 3))
  }
  return new ExprParser(ctx, argv).run()
}

/**
 * Recursive-descent `test` expression parser (>4 args, GNU expr grammar:
 * or -> and -> term with `!` and parentheses).
 */
class ExprParser {
  private pos = 0

  constructor(
    private readonly ctx: CondContext,
    private readonly argv: (string | PathSpec)[],
  ) {}

  private peek(offset = 0): string | null {
    const arg = this.argv[this.pos + offset]
    if (arg === undefined) return null
    return scopePath(arg)
  }

  async run(): Promise<boolean> {
    const result = await this.orExpr()
    if (this.pos !== this.argv.length) {
      throw new CondError(`${this.ctx.name}: too many arguments`)
    }
    return result
  }

  private async orExpr(): Promise<boolean> {
    let result = await this.andExpr()
    while (this.peek() === '-o') {
      this.pos += 1
      const right = await this.andExpr()
      result = result || right
    }
    return result
  }

  private async andExpr(): Promise<boolean> {
    let result = await this.term()
    while (this.peek() === '-a') {
      this.pos += 1
      const right = await this.term()
      result = result && right
    }
    return result
  }

  private async term(): Promise<boolean> {
    const tok = this.peek()
    if (tok === null) throw new CondError(`${this.ctx.name}: argument expected`)
    if (tok === '!') {
      this.pos += 1
      return !(await this.term())
    }
    if (tok === '(') {
      this.pos += 1
      const result = await this.orExpr()
      if (this.peek() !== ')') throw new CondError(`${this.ctx.name}: \`)' expected`)
      this.pos += 1
      return result
    }
    const nxt = this.peek(1)
    if (nxt !== null && BINARY_OPS.has(nxt) && this.peek(2) !== null) {
      const left = at(this.argv, this.pos)
      const right = at(this.argv, this.pos + 2)
      this.pos += 3
      return applyBinary(this.ctx, left, nxt, right)
    }
    if (UNARY_OPS.has(tok) && nxt !== null && nxt !== '-a' && nxt !== '-o') {
      const operand = at(this.argv, this.pos + 1)
      this.pos += 2
      return applyUnary(this.ctx, tok, operand)
    }
    this.pos += 1
    return tok !== ''
  }
}

/** Evaluate a flat test/[ argument list with bash's arity rules. */
export async function evalFlat(ctx: CondContext, argv: (string | PathSpec)[]): Promise<boolean> {
  const n = argv.length
  if (n === 0) return false
  if (n === 1) return evalOne(at(argv, 0))
  if (n === 2) return evalTwo(ctx, argv)
  if (n === 3) return evalThree(ctx, argv)
  if (n === 4) return evalFour(ctx, argv)
  return new ExprParser(ctx, argv).run()
}
