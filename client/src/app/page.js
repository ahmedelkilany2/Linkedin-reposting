
'use client';
import { useState } from "react";
import Image from 'next/image';



export default function LinkedinHomepage() {


  const [search, setSearch] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");


  return (

    <div className="flex min-h-full flex-1 flex-col justify-center px-6 py-20 lg:px-8 bg-gray-100">
      <div className="sm:mx-auto sm:w-full sm:max-w-sm">
      <Image
            alt="Your Company"
            src="/images/default-logo.png"
            width={500}
            height={500}
            className="mx-auto h-10 w-auto"
          />
        <h2 className="mt-6 text-center text-2xl/9 font-bold tracking-tight text-gray-900">
          LinkedIn Automation Tool
        </h2>
      </div>
      <h4 className="mt-3 text-center text-lg font-bold tracking-tight text-gray-900">
        Automatically find trending LinkedIn posts, generate fresh content, and publish it to your profile—no writing, no hassle, just results.
      </h4>

      <div className="mt-10 sm:mx-auto sm:w-full sm:max-w-sm">
        <form action="#" method="POST" className="space-y-6">
          <div >
            <div className="mt-3">
              <input
                id="email"
                name="email"
                type="email"
                required
                autoComplete="email"
                className="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 sm:text-sm/6"
                value={search}
                onChange={(e)=>{setSearch(e.target.value)}}
                placeholder="Search topic"
              />
            </div>
            <div className="mt-3">
              <input
                id="email"
                name="email"
                type="email"
                required
                className="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 sm:text-sm/6"
                value={email}
                onChange={(e)=>{setEmail(e.target.value)}}
                placeholder="LinkedIn email"
              />
            </div>
            <div className="mt-3">
              <input
                id="password"
                name="password"
                type="password"
                required
                className="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-indigo-600 sm:text-sm/6"
                value={password}
                onChange={(e)=>{setPassword(e.target.value)}}
                placeholder="LinkedIn password"
              />
            </div>

          </div>


          <div>
            <button
              type="submit"
              className="flex w-full justify-center rounded-md bg-indigo-600 px-3 py-1.5 text-sm/6 font-semibold text-white shadow-xs hover:bg-indigo-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600"
            >
              Submit
            </button>
          </div>
        </form>

        
      </div>
    </div>

  );
}
